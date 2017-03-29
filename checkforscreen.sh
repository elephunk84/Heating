#!/bin/bash

TEST=$(screen -ls | grep -c Heating)
NOTFOUND="0"
FOUND="1"
echo $TEST
echo "Found = " $FOUND "Not Found = " $NOTFOUND
case "$NOTFOUND" in 
 "$TEST" )
  echo "Not found, Starting..."
  screen -dm -S Heating bash -c "sudo python3 /home/iainstott/GitRepo/Heating/run.py"
  ;;
esac
