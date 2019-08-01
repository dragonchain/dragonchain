# Scheduler

Relevant To: Level 1 chains

## Overview

The scheduler is responsible for performing recurring actions on a chain on
a specific interval. This is currently only used to schedule recurring smart
contract invocations.

Actions can be scheduled with an interval (number of seconds between actions)
or with a
[cron expression](https://en.wikipedia.org/wiki/Cron#CRON_expression).

### Entrypoint

In order to run the scheduler, `sh entrypoints/scheduler.sh` should be used as
the command of the built docker container.

## Architecture

The scheduler takes advantage of
[APScheduler](https://pypi.org/project/APScheduler/) which parses for
timing events containing a cron expression or interval. APScheduler also
handles the actual triggers of the events themselves.

On top of APScheduler, the scheduler microservice keeps state of TimingEvents
for rescheduling.

To interact with the scheduler, the redis queue `mq:scheduler` is used.
Pushing a timing event to this queue will cause the change_poller to perform
the relevant
[CRUD](https://en.wikipedia.org/wiki/Create,_read,_update_and_delete) operation
on the requested timing event resource.
