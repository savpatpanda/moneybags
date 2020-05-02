import matplotlib.pyplot as plt

val = []

def app(v):
	global val
	val.append(v)

def graph(title):
	global val
	print(val)
	plt.plot(val)

	plt.title("%s : Dow Drop" % title)
	plt.savefig("./images/%s.png" % title)
	# plt.show()
	val.clear()
	plt.clf()
