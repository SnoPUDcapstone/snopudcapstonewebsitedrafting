firstly change the path in app.py to the csv file to create an api with

---------------------------------------------------------------
to run this visualization ensure flask is installed - 

pip install flask flask-cors pandas

next run 

-> python app.py 

in a terminal to setup server

-----------------------------------------------------------

finally, when you open index.html it should display a graph!

More to come, will update!!
------------------------------------------------------------
Change log - to implement still:

Machine Learning model --------------------------| not this quarter

results page ------------------------------------| X

known bugs:
  switching from soc or batter KW to solar while date selection is active does not return the date selection as solar, rather the current days solar
  toggling on and off solar while a date selection is active returns current day data
