Dragonchain Transactions
===

Dragonchain transactions are json and have the following format. 

Two sections containing key value pairs, a header, and a payload. 

The header has a fairly rigid format, it must have the following key-value pairs. 
"create_ts", "business_unit", "family_of_business", "owner", "transaction_type", and "entity". 

The payload section can hold any data encoded in a json format that you wish to post on the blockchain. 


```
{
  "header": {
    "create_ts": 1475180987,
    "business_unit": "a3e13076-8683-11e6-97a9-3c970e3bee11",
    "family_of_business": "Test Business Family",
    "line_of_business": "My Business",
    "owner": "Test Node",
    "transaction_type": "LOCATION_RECORD",
    "entity": "c78f4526-8683-11e6-b1c6-3c970e3bee11" 
  },
  "payload": {
"transactions":[
    { "sender":"john@example.org", "numberOfDragons":"10", "receiver": "mike@example.org"},
    { "sender":"bob@example.org", "numberOfDragons":"100", "receiver": "john@example.org"},
    { "sender":"fred@example.org", "numberOfDragons":"5", "receiver": "john@example.org"}
    ]}
  
}
```

As long as the json passes validation it should post to the transaction service correctly. 

Header Notes
===
You probably want to devote some time to thinking about your prefered scheme for dragonchain headers since they are searchable. 

create_ts - This should be a time stamp, and is typically the number of seconds since unix epoch. You can find out more about that at this (link)[https://en.wikipedia.org/wiki/Unix_time]

business_unit, family_of_business, line_of_business, owner - field are typically strings. Setting up a proper scheme for these headers enables you to easily query your transactions. These fields also can be used to trigger smart contracts. 

transaction_type - Typically a string, this is a queriable field for both smart contracts and the query service.

entity - Typically a string. This is a good field to use for interop with the application your using to create the transaction. (i.e. make it a unique guid  that both applications use, so you can query a transaction in both dragonchain, and your application). 


