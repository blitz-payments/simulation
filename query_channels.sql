select channels.short_channel_id, satoshis, nodes, base_fee_millisatoshi, fee_per_millionth, update_time
from channels
join (select pol.short_channel_id, direction, base_fee_millisatoshi, fee_per_millionth, delay, pol.update_time
	from policies as pol
	join (select short_channel_id, max(update_time) from policies group by short_channel_id) as maxpol 
	on pol.short_channel_id = maxpol.short_channel_id 
	and pol.update_time = maxpol.max
	order by pol.short_channel_id asc) as cp
on channels.short_channel_id = cp.short_channel_id
where channels.close ->> 'type' is NULL;
