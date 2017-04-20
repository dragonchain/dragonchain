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


BEGIN;
/* Don't drop tables unless you really want to */
--DROP TABLE transactions;
CREATE TABLE IF NOT EXISTS timestamps (

    timestamp_id UUID PRIMARY KEY,

    block_id INT,

    origin_id VARCHAR(256),

    /* confirm: when the transaction record was created */
    create_ts timestamptz,

    /* boolean field to indicate whether a transaction was successfully sent */
    timestamp_receipt boolean not null DEFAULT FALSE,

    /* Signature block - includes public key */
    signature JSON,

    /* arbitrary info per phase */
    verification_info JSON
);
COMMIT;
BEGIN;
GRANT ALL ON timestamps to blocky;
COMMIT;