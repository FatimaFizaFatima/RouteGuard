import time
from app.breakers import CircuitBreaker

b = CircuitBreaker(failure_limit=2, cooldown_s=0.2)
print(b.allow(), b.state)            
b.record_failure(); print(b.state)   
b.record_failure(); print(b.state)   
print(b.allow())                     
time.sleep(0.25)
print(b.allow(), b.state)           
print(b.allow())                     
b.record_failure(); print(b.state)   
time.sleep(0.25)
print(b.allow())                    
b.record_success(); print(b.state, b.failures)  