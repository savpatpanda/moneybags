# moneybags

## develop
### create environment and install libraries
```
python3 -m venv env
source ./env/bin/activate
pip3 install requirements.txt
```
## simulate & optimize
```
python3 algorithm.py sim # simulate performance over a certain time period
python3 algorithm.py opt # run simulations over permutations of hyperparameters and return the optimal policy
```


