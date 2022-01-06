#!/usr/bin/env bash

docker save word-align | ssh <ENTER_SERVER_HERE> docker load