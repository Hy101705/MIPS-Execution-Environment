# Build the MIPS execution environment.

ifneq (, $(shell which dcc))
CC	= dcc
else ifneq (, $(shell which clang))
CC	= clang
else
CC  = gcc
endif

EXERCISES	?=
CLEAN_FILES	?=

.DEFAULT_GOAL	= all
.PHONY: all clean

-include *.mk

all:	${EXERCISES}

clean:
	-rm -f ${CLEAN_FILES}
