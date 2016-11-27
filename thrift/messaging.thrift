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

/* Verifications */
struct VerificationSignature {
    /* the private key based signature of the signing_hash */
    1: string signature,
    /* the message contained in the signature */
    2: string signing_hash
}

struct PriorBlockHash {
    /* a hash of verfications */
    1: string hash,
    /* the list of ids representing the verifications included in the prior block hash */
    2: list<string> verification_ids
}

struct Verification {
    1: string verification_id,
    2: string verified_ts,
    3: i32 block_id,
    4: VerificationSignature signature,
    5: string owner,
    6: list<string> transaction_ids,
    7: list<string> verification_ids,
    8: PriorBlockHash previous_block_hash
}

/* Transactions */
enum Status {
    NEW = 1,
    PENDING = 2,
    APPROVED = 3,
    COMPLETE = 4
}

struct Header {
    1: string actor,
    2: i32 block_id,
    3: string business_unit,
    4: i32 create_ts,
    5: optional i32 creator_id,
    6: string entity,
    7: string family_of_business,
    8: string line_of_business,
    9: string owner,
    10: string status,
    11: string transaction_id,
    12: i32 transaction_ts,
    13: string transaction_type
}

struct Signature {
    1: optional string signatory,
    2: string hash,
    3: optional string strip_hash,
    4: string signature,
    5: string public_key,
    6: i32 signature_ts,
    7: optional string child_signature /* child signature */
}

struct Payload {
    1: map<string, string> action,
    2: string swid
}

struct Transaction {
    1: Header tx_header,
    2: optional string tx_payload,
    3: Signature tx_signature
}

struct Node {
    1: string host,
    2: i16 port,
    3: string owner,
    4: string node_id,
    5: i32 phases
}

struct VerificationRecordCommonInfo {
    1: i32 block_id,
    2: string origin_id,
    3: i32 phase,
    4: i32 verification_ts,
    5: Signature signature,
    6: string prior_hash,
    7: string lower_hash,
    8: map<string, bool> public_transmission
}

struct Phase_1_msg {
    1: VerificationRecordCommonInfo record,
    2: list<Transaction> transactions
}

struct Phase_2_msg {
    1: VerificationRecordCommonInfo record,
    2: list<Transaction> valid_txs,
    3: list<Transaction> invalid_txs,
    4: string business,
    5: string deploy_location
}

/* TODO: rename business_list and deploy_loc_list to businesses and deploy_locations respectively */
struct Phase_3_msg {
    1: VerificationRecordCommonInfo record,
    2: list<string> lower_hashes,
    3: i32 p2_count,
    4: list<string> businesses,
    5: list<string> deploy_locations
}

struct Phase_4_msg {
    1: VerificationRecordCommonInfo record
}

union VerificationRecord {
    1: Phase_1_msg p1,
    2: Phase_2_msg p2,
    3: Phase_3_msg p3,
    4: Phase_4_msg p4
}

union Phase_5_msg {
    1: Transaction transaction,
    2: VerificationRecord verification_record,
    /* Level 5 node will NOT hash this field */
    3: string hash,
    /* Level 5 node WILL hash this field */
    4: string misc
}

exception UnauthorizedException {
}

/* RMI Service */
service BlockchainService {

   void ping(),

   Node get_node_info() throws (1:UnauthorizedException unauthorized),

   /* Request permission to connect and use a randomly generated pass phrase to prevent node_id spoofing*/
   bool register_node(1: Node node, 2: string pass_phrase) throws (1:UnauthorizedException unauthorized),

   oneway void unregister_node(1: string pass_phrase),

   void phase_1_message(1: Phase_1_msg p1),

   void phase_2_message(1: Phase_2_msg p2),

   void phase_3_message(1: Phase_3_msg p3),

   /* external partner notary phase */
   void phase_4_message(1: Phase_4_msg p4),

   /* public, Bitcoin bridge phase */
   void phase_5_message(1: Phase_5_msg p5),

   list<Node> get_peers() throws (1:UnauthorizedException unauthorized)
}