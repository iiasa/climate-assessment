#!/bin/bash

docker build -t climate-assessment-nb .

docker run -it --rm -p 8888:8888 climate-assessment-nb
