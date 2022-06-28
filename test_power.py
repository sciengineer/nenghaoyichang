import math
import matplotlib.pyplot as plt
b = -math.sqrt(2)
c = b
list_c = []
list_abs_c = []
for i in range(100):
    # c = pow(b,c)
    c = b ** c
    print(c)