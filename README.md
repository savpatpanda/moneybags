# moneybags

## develop
### create environment and install libraries
```
python3 -m venv env
source ./env/bin/activate
pip3 install requirements.txt
mkdir sim
mkdir images
```
## simulate & optimize
```
python3 algorithm.py sim # simulate performance over a certain time period
python3 algorithm.py opt # run simulations over permutations of hyperparameters and return the optimal policy
```
These will save matplot graphs of your initial balance to the images directory and metadata to the sim directory (txt files).


