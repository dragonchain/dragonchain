/*

Copyright 2016 Disney Connected and Advanced Technologies

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
__copyright__ = "Copyright 2016, Disney Connected and Advanced Technologies"
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
--DROP TABLE transactions;
CREATE TABLE IF NOT EXISTS transactions (

    transaction_id UUID PRIMARY KEY,

    /* confirm: when the transaction happened */
    transaction_ts timestamptz,

    /* confirm: when the transaction record was created */
    create_ts timestamptz,

    /* what are a few examples? */
    business_unit VARCHAR(256),

    /* what are a few examples? */
    family_of_business VARCHAR(256),

    /* what are a few examples? */
    line_of_business VARCHAR(256),

    /* what are a few examples? */
    payload JSON,

    /* signatures */
    signature JSON,

    /* what are a few examples? */
    owner VARCHAR(256),

    /* what are a few examples? */
    creator_id VARCHAR(256),

    /* arbitrary field, coming from the creator
     * creator type:  Point of Sale or Profile? */
    transaction_type VARCHAR(256),
    /* arbitrary field for describing the whos associated with the tx */
    actor VARCHAR(256),
    /* arbitrary field describing the item or asset associated with the tx */
    entity VARCHAR(256),

    block_id INT,

    status transaction_status
);
COMMIT;
BEGIN;
GRANT ALL ON transactions to blocky;
COMMIT;

BEGIN;
/* Don't drop tables unless you really want to */
--DROP TABLE block_verifications;
CREATE TABLE IF NOT EXISTS block_verifications (

    verification_id UUID PRIMARY KEY,

    verification_ts timestamptz,

    block_id INT,

    /* Signature block - includes public key */
    signature JSON,

    /* Verifying node identifier */
    origin_id VARCHAR(256),

    phase INT,

    /* arbitrary info per phase */
    verification_info JSON,

    /* XOR'd hashes of signatures from the previous verification step */
    previous_block_hash JSON

    /* block status?? */
);
COMMIT;
BEGIN;
GRANT ALL ON block_verifications to blocky;
COMMIT;
