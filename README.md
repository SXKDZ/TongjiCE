# TongjiCE
*Automatically course selection for Tongji University*

MIT Licence

By SXKDZ with support of lisirrx

**Disclaimer: use with your own discretion!**



## Usage

- Enter matriculation ID and password to login.
- Choose the entrance for course selection.
- Select course ID and section ID.
- Set parameters for interval between attempts and the maximum number of attempts.
- Wait and see the results!

## Compiling and Publish

To publish a precompiled version of `TongjiCE`, install `cx_freeze` by typing:

```
pip install cx_freeze
```

Then acquire phantomjs of your platform at [here](http://phantomjs.org/download.html) and place the executable file `phantomjs` in the root directory.

Then type:

```
python setup.py build
```

to compile and get the executable files in the `build` folder.

## Dependencies

- Python 3.6+
- phantomjs


- See `requirements.txt` for details.