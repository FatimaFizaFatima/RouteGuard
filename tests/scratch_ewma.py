from app.executor import update_latency

lat = {}
update_latency(lat, "m", 1000)
print(lat["m"])     
update_latency(lat, "m", 2000)
print(lat["m"])     
update_latency(lat, "m", 1000)
print(lat["m"])      