ISO 8583 Simulator
==================


About
-----

This is an Open source simulator that takes in ISO 8583 messages (messaging protocol used by Banks, Payment Processor, CHs and other financial Institutions)



This program consists of a command line app that can be used to simulate various types of messages, for Sale, Void, Reversal and Auth. You can preconfigure  merchant IDs and Credit cards list (or hashed values of credit card) for testing.
Although this is self contained its functionality can extended by linking to a Host System wher ethe processing logic can be more complex. 

Reports are generated after each run for passed and failed tests.



Run
---

Create an executable

`pyinstaller start.py`


Or, run directly

`python start.py`



Enjoy.


TODO
----
- Convert to a Web App/Service.
- Add Kafka Integration