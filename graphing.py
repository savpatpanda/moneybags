import matplotlib.pyplot as plt

sell_index = [144,160,170,194]
buy_index = [42,58,66,82,345]
filename = 'GOOG.txt'

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
