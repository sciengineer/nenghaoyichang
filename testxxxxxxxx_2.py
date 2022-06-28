import math
import matplotlib.pyplot as plt
b = -math.sqrt(2)
c = b
list_c = []
list_abs_c = []
for i in range(8):
    c = b**c

    print(c)
    list_c.append(c)
    list_abs_c.append(abs(c))
plt.plot(list_c)
plt.plot(list_abs_c)
plt.show()
