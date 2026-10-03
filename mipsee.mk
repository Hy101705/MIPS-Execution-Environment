CFLAGS =

ifneq (, $(shell which dcc))
CC	?= dcc
else
CC	?= clang
CFLAGS += -Wall
endif

EXERCISES	  += mipsee

SRC = mipsee.c
INCLUDES =

# if you add extra .c files, add them here
SRC +=

# if you add extra .h files, add them here
INCLUDES +=


mipsee:	$(SRC) $(INCLUDES)
	$(CC) $(CFLAGS) $(SRC) -o $@

PYTHON ?= python3
.PHONY: test
test: mipsee
	$(PYTHON) tests/run_tests.py

.PHONY: test-s1 test-s2 test-s3 test-s4 test-policy
test-s1: mipsee
	$(PYTHON) tests/run_tests.py --subset S1
test-s2: mipsee
	$(PYTHON) tests/run_tests.py --subset S2
test-s3: mipsee
	$(PYTHON) tests/run_tests.py --subset S3
test-s4: mipsee
	$(PYTHON) tests/run_tests.py --subset S4
test-policy: mipsee
	$(PYTHON) tests/run_tests.py --subset POLICY
