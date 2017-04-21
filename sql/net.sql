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
CREATE TABLE IF NOT EXISTS nodes (
    /* node unique id */
    node_id UUID PRIMARY KEY,

    /* confirm who created the node */
    node_owner VARCHAR(256),

    /* host name */
    host VARCHAR(256),

    /* port number */
    port VARCHAR(256),

    /* phases provided */
    phases BIT(5),

    /* priority level of node */
    priority_level INT DEFAULT 10000,

    /* node pass phrase */
    pass_phrase VARCHAR(256),

    /* node signature */
    public_key VARCHAR(256),

    /* time node record was created */
    create_ts timestamptz,

    /* last connection time (reset on failed connection) */
    start_conn_ts timestamptz,

    /* last activity time */
    last_activity_ts timestamptz,

    /* time of last failed connection (reset on successful connection) */
    last_conn_attempt_ts timestamptz,

    /* number of connection attempts with failure (reset on successful connection) */
    connection_attempts INT,

    /* connection latency */
    latency INT
);

COMMIT;
BEGIN;
GRANT ALL ON nodes to blocky;
COMMIT;