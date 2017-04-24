/*

Copyright 2017, Dragonchain Foundation

Licensed under the Apache License, Version 2.0 (the "Apache License")
with the following modification; you may not use this file except in
compliance with the Apache License and the following modification to it:
Section 6. Trademarks. is deleted and replaced with:

     6. Trademarks. This License does not grant permission to use the trade
        names, trademarks, service marks, or product names of the Licensor
        and its affiliates, except as required to comply with Section 4(c) of
        the License and to reproduce the content of the NOTICE file.

You may obtain a copy of the Apache License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the Apache License with the above modification is
distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied. See the Apache License for the specific
language governing permissions and limitations under the Apache License.

__author__ = "Joe Roets, Brandon Kite, Dylan Yelton, Michael Bachtel"
__copyright__ = "Copyright 2017, Dragonchain Foundation"
__license__ = "Apache"
__version__ = "2.0"
__maintainer__ = "Joe Roets"
__email__ = "joe@dragonchain.org"

*/


/* Create a blocky user if it doesn't exist */
do
$body$
declare
  num_users integer;
begin
   SELECT count(*)
     into num_users
   FROM pg_user
   WHERE usename = 'blocky';

   IF num_users = 0 THEN
      CREATE ROLE blocky WITH LOGIN;
   END IF;
end
$body$
;

BEGIN;
/* Don't drop tables unless you really want to */
CREATE TABLE IF NOT EXISTS smart_contracts (
    /* sc unique id */
    sc_id UUID PRIMARY KEY,

    /* type of sc (i.e. tsc, ssc, lsc, bsc, etc.) */
    sc_class VARCHAR(256),

    /* smart contract code */
    smart_contract TEXT,

    /* sc dictionary key */
    sc_key VARCHAR(256),

    /* criteria used for selection of appropriate sc */
    criteria TEXT[],

    /* unit test for sc */
    test TEXT,

    /* required libraries needed for the sc to run */
    requirements TEXT[],

    /* current sc version */
    version INT,

    /* sc status */
    status sc_status
);
COMMIT;
BEGIN;
GRANT ALL ON smart_contracts to blocky;
COMMIT;