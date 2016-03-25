#!/bin/bash

fswatch -o .. | xargs -n1 make html
