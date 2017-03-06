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
CREATE TABLE IF NOT EXISTS sub_to (
  subscription_id UUID PRIMARY KEY,

  /* subscribee id */
  subscribed_node_id UUID,

  /* confirm who created the node */
  node_owner VARCHAR(256),

  /* subscribee host */
  host VARCHAR(256),

  /* subscribee port */
  port INTEGER,

  /* criteria to be met by subscribee */
  criteria JSON,

  /* time in seconds between requesting transactions from subscribee */
  synchronization_period INTEGER DEFAULT 5,

  /* last time a request was made to subscribee for data */
  last_time_called timestamptz DEFAULT CURRENT_TIMESTAMP,

  /* time subscription was created */
  create_ts timestamptz,

  /* subscription status */
  status subscription_status
);
COMMIT;
BEGIN;
GRANT ALL ON sub_to to blocky;
COMMIT;

BEGIN;
CREATE TABLE IF NOT EXISTS sub_from (
  subscriber_id UUID PRIMARY KEY,

  /* transaction criteria to be met for subscriber */
  criteria JSON,

  /* Indicates whether the subscription criteria for this block is satisfied */
  phase_criteria INT,

  subscriber_public_key VARCHAR(256),

  /* time subscription was created */
  create_ts timestamptz
);
COMMIT;
BEGIN;
GRANT ALL ON sub_from to blocky;
COMMIT;

BEGIN;
/* Don't drop tables unless you really want to */
CREATE TABLE IF NOT EXISTS sub_vr_backlog (
    transfer_id UUID PRIMARY KEY,
    /* The node to transmit this block to */
    client_id VARCHAR(256),
    /* block id */
    block_id INT
);
COMMIT;
BEGIN;
GRANT ALL ON sub_vr_backlog to blocky;
COMMIT;

BEGIN;
CREATE TABLE IF NOT EXISTS sub_vr_transfers (
  /* The node to transmit this record to */
  transfer_to VARCHAR(256),

  transactions JSON[],

  verifications JSON[]
);
COMMIT;
BEGIN;
GRANT ALL ON sub_vr_transfers to blocky;
COMMIT;

/* used to accelerate queries from subscription clients for blocks that are ready to transfer */
BEGIN;
CREATE INDEX sub_vr_backlog_rdy_to_transfer_idx ON sub_vr_backlog (client_id);
COMMIT;

/* used to accelerate queries when verification records are received to see if criteria has been satisfied */
BEGIN;
CREATE INDEX sub_vr_backlog_criteria_check_idx ON sub_vr_backlog (block_id);
COMMIT;