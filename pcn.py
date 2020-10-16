import networkx as nx
import pandas as pd
from typing import List
import constants as cons
from collections import defaultdict

PREFIX_BAL = 'b-'
PREFIX_LOCKED = 'l-'
SUFFIX_SMALL = 's'
SUFFIX_LARGE = 'l'


class PCN:

    def __init__(self, channels: pd.DataFrame, linear_collateral: int) -> None:
        """
        Create a new PCN instance from a pd.DataFrame that holds the channels.
        The channels in a PCN will have attributes containing information about
        the balance (shared and individual) and about fees.
        Note that since it is unknown how much balance each user holds currently 
        (this information is private), we assume that the total balance is initially
        shared. After using it to pay in a certain direction, it becomes individual 
        balance of the recipient.
        ----------
        Parameters
        ----------
        channels : pd.DataFrame
            A DataFrame containing bidirectional channels between 'nodeA' and 'nodeB' 
            (both of which areunique int identifiers)
            Additional columns: 'satoshis' containing the total balance of the channel, 
            'base_fee' and 'relative_fee' containing the fee information of the channel
            These column names are specified in constants.py
        """
        self.graph = nx.from_pandas_edgelist(channels, cons.NODE_A, cons.NODE_B, [cons.SATOSHIS, cons.BF, cons.FR])
        # To keep assign attributes to both nodes individually, we distinguish by comparing their id (an integer)
        # The smaller id takes the SUFFIX_SMALL, the larger on the SUFFIX LARGE.
        # As the ids are unique, they cannot clash
        # Add attributes for keeping track of the individual balance of nodes in this channel
        nx.set_edge_attributes(self.graph, 0, self.__bal_identifier(SUFFIX_SMALL))
        nx.set_edge_attributes(self.graph, 0, self.__bal_identifier(SUFFIX_LARGE))
        # Add attributes for keeping track of amount of locked coins of nodes in this channel
        nx.set_edge_attributes(self.graph, 0, self.__lock_identifier(SUFFIX_SMALL))
        nx.set_edge_attributes(self.graph, 0, self.__lock_identifier(SUFFIX_LARGE))
        if linear_collateral != cons.CONSTANT and linear_collateral != cons.LINEAR:
            raise ValueError('Invalid linear_collateral, has to be cons.CONSTANT or cons.LINEAR.')
        self.linear = linear_collateral
        self.round = 0
        self.revertMap = defaultdict(list)
        self.unlockMap = defaultdict(list)

    def set_round(self, r: int) -> None:
        """
        Set the current simulation round of this PCN to [r]. This will unlock/revert all the payments that 
        were previously locked until round [r].
        """
        self.round = r
        unlockVal = self.unlockMap[r]
        if unlockVal != None and unlockVal != []:
            for (u, v, amount) in unlockVal:
                self.unlock(u, v, amount)
        del self.unlockMap[r]
        revertVal = self.revertMap[r]
        if revertVal != None and revertVal != []:
            for (u, v, amount) in revertVal:
                self.revert(u, v, amount)
        del self.revertMap[r]

    def pay_malicious(self, path: List[int], amount: int, malicious_path_index: int, fault_type: int) -> int:
        """
        Carry out a malicious payment. Given a payment [path], an [amount], an index (0 < malicious_path_index 
        < len(path)) and a fault_type, locks the coins up until the malicious node. Should there be insufficient 
        balance in a channel before, INSUF_BAL is returned and the coins are unlocked. Otherwise, the coins stay 
        locked and are added to either the revertMap (FAIL2) or the unlockMap (FAIL1), to be unlocked at a certain 
        round. Note that in the case of linear==0 and FAIL2, the funds are immediately unlocked (nothing happens).
        """
        pay_status = fault_type
        if fault_type == cons.FAIL2 and self.linear == cons.CONSTANT:
            return pay_status
        if malicious_path_index <= 0 or malicious_path_index > len(path) - 1:
            raise ValueError('The malicious node has to be an index on the path that is not the sender.')
        a = amount
        a_after_mal = amount
        # Check if there is enough balance
        for i in range(0, len(path)-1):
            u = path[i]
            v = path[i + 1]
            if self.get_balance_u_in_uv(u, v) < a:  # payment unsuccessful
                return pay_status
            fee = self.graph[u][v][cons.BF] + round((self.graph[u][v][cons.FR] * a) / 1000000)
            a = max(a - fee, 0)
            if i == (malicious_path_index - 1):
                a_after_mal = a  # save amount after fees at malicious node
                if self.linear == cons.LINEAR:  # in case of Lightning, stop checking after malicious node
                    break
        a = a_after_mal
        # Lock coins for Blitz
        if self.linear == cons.CONSTANT:
            for i in range(malicious_path_index, len(path)-1):
                u = path[i]
                v = path[i + 1]
                self.lock(u, v, a)
                self.unlockMap[self.round + cons.DELAY_ROUNDS].append(tuple((u, v, a)))
                fee = self.graph[u][v][cons.BF] + round((self.graph[u][v][cons.FR] * a) / 1000000)
                a = max(a - fee, 0)
        # Lock coins for LN
        elif self.linear == cons.LINEAR:
            for i in range(0, malicious_path_index):
                u = path[i]
                v = path[i + 1]
                lock_time = (len(path) - 1 - i) * cons.DELAY_ROUNDS
                self.lock(u, v, amount)
                if fault_type == cons.FAIL2:
                    self.revertMap[self.round + lock_time].append(tuple((u, v, amount)))
                elif fault_type == cons.FAIL1:
                    self.unlockMap[self.round + lock_time].append(tuple((u, v, amount)))
                fee = self.graph[u][v][cons.BF] + round((self.graph[u][v][cons.FR] * amount) / 1000000)
                amount = max(amount - fee, 0)
        return fault_type

    def pay(self, path: List[int], amount: int) -> int:
        """
        Given a payment [path] and an [amount], carries out a payment, deducting the 
        according fee at every hop.
        If there is enough enough balance, the payment is successful and returns SUCCESS,
        if the balance is insufficient in any channel on the path, returns INSUF_BAL.
        (These return values are found in constants.py)
        """
        lock_list = []
        pay_status = cons.SUCCESS
        for i in range(0, len(path) - 1):
            u = path[i]
            v = path[i + 1]
            if self.get_balance_u_in_uv(u, v) < amount:  # payment unsuccessful
                pay_status = cons.INSUF_BAL
                break
            self.lock(u, v, amount)
            lock_list.append(tuple((u, v, amount)))
            fee = self.graph[u][v][cons.BF] + round((self.graph[u][v][cons.FR] * amount) / 1000000)
            amount = max(amount - fee, 0)
        if pay_status == cons.SUCCESS:  # unlock balances in successful case
            for (u, v, a) in lock_list:
                self.unlock(u, v, a)
        else:  # (pay_status == cons.INSUF_BAL) revert payment in unsuccessful case
            for (u, v, a) in lock_list:
                self.revert(u, v, a)
        return pay_status

    def get_balance_u_in_uv(self, u: int, v: int) -> int:
        """
        Returns the (shared + individual) balance of [u] in the channel ([u], [v]), an integer.
        """
        (s_u, _) = self.__get_uv_suffix(u, v)
        return self.graph[u][v][self.__bal_identifier(s_u)] + self.graph[u][v][cons.SATOSHIS]

    def lock(self, u: int, v: int, amount: int) -> None:
        """
        If [u] holds enough balance in the channel ([u],[v]), then lock [amount] coins in this channel for [u].
        """
        (s_u, _) = self.__get_uv_suffix(u, v)
        bal_id_u = self.__bal_identifier(s_u)
        bal_s = self.__get_balance_u_in_uv(u, v, bal_id_u)
        if bal_s < amount:  # total balance not enough
            raise ValueError(f'Not enough balance ({bal_s}) for {u} in channel ({u},{v}) for locking {amount}.')
        elif self.graph[u][v][bal_id_u] >= amount:  # individual balance alone enough
            self.graph[u][v][bal_id_u] -= amount
        else:  # else use shared and individual balance
            self.graph[u][v]['satoshis'] -= (amount - self.graph[u][v][bal_id_u])
            self.graph[u][v][bal_id_u] = 0
        lock_id_u = self.__lock_identifier(s_u)
        self.graph[u][v][lock_id_u] += amount

    def unlock(self, u: int, v: int, amount: int) -> None:
        """
        If [u] has enough coins locked in the channel ([u],[v]), then unlock [amount] coins and give them to [v].
        """
        (s_u, s_v) = self.__get_uv_suffix(u, v)
        lock_id_u = self.__lock_identifier(s_u)
        if self.graph[u][v][lock_id_u] < amount:
            raise ValueError(
                f'Not enough coins {self.graph[u][v][lock_id_u]} locked for {u} in channel ({u},{v}) for unlocking {amount}.')
        self.graph[u][v][lock_id_u] -= amount
        bal_id_v = self.__bal_identifier(s_v)
        self.graph[u][v][bal_id_v] += amount

    def revert(self, u: int, v: int, amount: int) -> None:
        """
        If [u] has enough coins locked in the channel ([u],[v]), then revert, i.e., unlock [amount] coins and give them to [u].
        """
        (s_u, _) = self.__get_uv_suffix(u, v)
        lock_id_u = self.__lock_identifier(s_u)
        if self.graph[u][v][lock_id_u] < amount:
            raise ValueError(
                f'Not enough coins {self.graph[u][v][lock_id_u]} locked for {u} in channel ({u},{v}) for reverting {amount}.')
        self.graph[u][v][lock_id_u] -= amount
        bal_id_u = self.__bal_identifier(s_u)
        self.graph[u][v][bal_id_u] += amount

    def get_wormhole_potential(self, path: List[int], amount) -> int:
        """
        Given a payment [path] and an [amount], returns the maximal number of fees that can potentially be stolen
        with a wormhole attack
        """
        if len(path) < 5:
            return 0
        fees = 0
        for i in range(1, len(path)-3):
            u = path[i]
            v = path[i+1]
            fees += self.graph[u][v][cons.BF] + round((self.graph[u][v][cons.FR] * amount) / 1000000)
        return fees

    def get_total_fees(self, path: List[int], amount) -> int:
        """
        Given a payment [path] and an [amount], returns the total fees charged for this payment
        """
        fees = 0
        for i in range(1, len(path)-1):
            u = path[i]
            v = path[i+1]
            fees += self.graph[u][v][cons.BF] + round((self.graph[u][v][cons.FR] * amount) / 1000000)
        return fees

    def __get_balance_u_in_uv(self, u: int, v: int, bal_id_u: str) -> int:
        """
        Internal method to retrieve balance given a balance identifier.
        """
        return self.graph[u][v][bal_id_u] + self.graph[u][v][cons.SATOSHIS]

    @staticmethod
    def __get_uv_suffix(u: int, v: int) -> (int, int):
        """
        Internal method to retrieve the suffix depending on whether one id is larger than the other.
        """
        if u > v:
            return (SUFFIX_LARGE, SUFFIX_SMALL)
        elif u < v:
            return (SUFFIX_SMALL, SUFFIX_LARGE)
        else:  # u == v:
            raise ValueError('Channels are not reflexive. u and v cannot be the same')

    @staticmethod
    def __bal_identifier(suffix: str) -> str:
        """
        Internal static method construct a balance identifier from a given suffix.
        """
        if suffix == SUFFIX_SMALL or suffix == SUFFIX_LARGE:
            return PREFIX_BAL + suffix
        raise ValueError('Invalid suffix')

    @staticmethod
    def __lock_identifier(suffix: str) -> str:
        """
        Internal static method construct a lock identifier from a given suffix.
        """
        if suffix == SUFFIX_SMALL or suffix == SUFFIX_LARGE:
            return PREFIX_LOCKED + suffix
        raise ValueError('Invalid suffix')
