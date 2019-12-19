Dragonchain
===========

Welcome to the documentation for Dragonchain core!

The Dragonchain platform attempts to simplify integration of real business
applications onto a blockchain. Providing features such as easy integration,
protection of business data, fixed 5 second blocks, currency agnosticism, and
interchain features, Dragonchain shines a new and interesting light on
blockchain technology.

Intro
-----

These docs are meant to supply an overview of the Dragonchain source
code and architecture for the purpose of developing Dragonchain core.

These docs are NOT intended to demonstrate how to interact with a dragonchain
via the use of tools/SDKs. For that information, please view their relevant
documentation instead.

Source Code
-----------

All of the source code, as well as issue tracker can be viewed `on github <https://github.com/dragonchain/dragonchain/>`_.

.. toctree::
   :caption: Overview
   :maxdepth: 2

   overview/design_goals
   overview/architecture
   overview/changelog

.. toctree::
   :caption: Deployment
   :maxdepth: 2

   deployment/requirements
   deployment/dragonnet
   deployment/deploying
   deployment/links
   deployment/raspberry_pi
   deployment/migrating_v4

.. toctree::
   :caption: Usage
   :maxdepth: 2

   usage/authentication
   usage/permissioning

.. toctree::
   :caption: Components
   :maxdepth: 2

   components/webserver
   components/transaction_processor
   components/broadcast_processor
   components/contract_invoker
   components/job_processor
   components/contract_builder
   components/scheduler

.. toctree::
   :caption: Meta
   :maxdepth: 1

   meta/issues
   meta/community
   meta/contributing
   meta/license
