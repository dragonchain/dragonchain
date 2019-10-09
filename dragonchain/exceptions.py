# Copyright 2019 Dragonchain, Inc.
# Licensed under the Apache License, Version 2.0 (the "Apache License")
# with the following modification; you may not use this file except in
# compliance with the Apache License and the following modification to it:
# Section 6. Trademarks. is deleted and replaced with:
#      6. Trademarks. This License does not grant permission to use the trade
#         names, trademarks, service marks, or product names of the Licensor
#         and its affiliates, except as required to comply with Section 4(c) of
#         the License and to reproduce the content of the NOTICE file.
# You may obtain a copy of the Apache License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the Apache License with the above modification is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the Apache License for the specific
# language governing permissions and limitations under the Apache License.

"""
Base exception classes
"""


class DragonchainException(Exception):
    """Base exception"""


"""
DragonchainExceptions
"""


class ContractConflict(DragonchainException):
    """Exception raised when a user submits a contract name that already exists"""


class ContractLimitExceeded(DragonchainException):
    """Exception raised when a user has too many contracts to create more"""


class InvalidNodeLevel(DragonchainException):
    """Exception raised when user provides a node level which doesn't exist"""


class BadImageError(DragonchainException):
    """Exception raised when Dragonchain repo could not be parsed"""


class BadDockerAuth(DragonchainException):
    """Exception raised when user provided auth cannot be used"""


class ContractException(DragonchainException):
    """Exception raised when a contract modification fails"""


class OpenFaasException(DragonchainException):
    """Exception raised when OpenFaaS returns with error status"""


class LabChainForbiddenException(DragonchainException):
    """Exception raised when lab chain action is not allowed"""


class NotFound(DragonchainException):
    """Exception raised when object is not found"""


class BadRequest(DragonchainException):
    """Exception raised on bad request"""


class ValidationException(DragonchainException):
    """Exception raised when schema is invalid"""


class ActionForbidden(DragonchainException):
    """Exception raised when an action is forbidden"""


class UnauthorizedException(DragonchainException):
    """Exception raised by authorization when the user is not allowed to perform an action"""


class APIRateLimitException(DragonchainException):
    """Exception raised when the API Rate Limit is reached for a key"""


class ContractInvocationError(DragonchainException):
    """Exception raised when there is an error invoking a contract"""


class TransactionTypeConflict(DragonchainException):
    """Exception raised by the Transaction Type Registry when attempted register is existing"""


class InterchainConflict(DragonchainException):
    """Excepiton raised when trying to create an interchain with a name that already exists"""


class InsufficientFunds(DragonchainException):
    """Exception raised by the call to matchmaking for a claimcheck"""


class NotEnoughCrypto(DragonchainException):
    """Exception raised when creating an interchain transaction doesn't have enough funded crypto"""


class InvalidTransactionType(DragonchainException):
    """Exception used when transaction type is invalid"""


class ContractImageTooLarge(DragonchainException):
    """Exception raised by the job processor when a customer image is too large"""


class TimingEventSchedulerError(DragonchainException):
    """Exception raised when there is an error changing the state of a timing event"""


class BadStateError(DragonchainException):
    """Exception raised by a resource when it is in a state where the action is not permitted"""


class NotAcceptingVerifications(DragonchainException):
    """
    Exception raised by a the broadcast system when trying to add a verification of a certain
    level for a block that isn't accepting verifications for that particular level
    """


class NotEnoughVerifications(DragonchainException):
    """
    Raises when verifications are requested for a block that doesn't have enough,
    according to node requirements
    """


class AddressRegistrationFailure(DragonchainException):
    """Exception raised when a bitcoin address fails to register with the BTC node"""


class LedgerError(DragonchainException):
    """Exception raised when there is an error ledgering data on to the chain"""


class StorageError(DragonchainException):
    """Exception raised when there is a storage/cache error"""


class SanityCheckFailure(DragonchainException):
    """Exception raised when sanity check fails"""


class RPCError(DragonchainException):
    """Exception raise when RPC has an error"""


class APIError(DragonchainException):
    """Exception raise when API has an error"""


class RPCTransactionNotFound(DragonchainException):
    """Exception raised when a transaction is not found on an interchain network"""


class RedisearchFailure(DragonchainException):
    """Exception raised when redisearch fails"""


class MatchmakingError(DragonchainException):
    """Exception raised by matchmaking client when a problem has occurred"""


class PartyError(DragonchainException):
    """Exception raised by party client when a problem has occurred"""
