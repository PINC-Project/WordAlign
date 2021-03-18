#!/usr/bin/env bash

docker save word-align | ssh guest@korzinek.com docker load