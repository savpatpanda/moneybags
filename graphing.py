import matplotlib.pyplot as plt

sell_index = [647,1026,1433,1914]
buy_index = [71,128,995,1046,1569,1609,1633,1649,1665,1681,1697,1777,2306,2439]
filename = 'sim/GS.txt'

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
