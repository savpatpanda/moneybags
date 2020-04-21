import matplotlib.pyplot as plt

sell_index = [140,146,158,164,192,199,231,267]
buy_index = [21,28,40,46,58,64,76,82,90,96,124]
filename = 'sim/GOOG.txt'

val = []
with open(filename, 'r') as f:	
	for line in f:
		val.append(float(line))

stock = filename[:-4]
plt.plot(val,'-k')

for i in range(len(val)):
	if i in sell_index:
		plt.plot(i,val[i],color='red',marker='o',markersize=8)
	elif i in buy_index:
		plt.plot(i,val[i],color='green',marker='o',markersize=8)

plt.title(stock)
plt.show()
