#!/bin/bash
# Assumes that the database name and password are kept in a secure directory
set -e
DATETIME=`date +"%Y%m%d%H%M"`
SQL_DIR="$HOME/mysql"
DB_NAME=`cat $SQL_DIR/db_name`
PASSWD=`cat $SQL_DIR/passwd`
SQL_REPO="$SQL_DIR/SCOOP-data-quality/PolypharmacySQLQueries"
cd $SQL_REPO
mysql -h 127.0.0.1 -P 3307 -u oscarb --database=$DB_NAME -n -vvv -t -AU --password=$PASSWD < All_queries.sql > $SQL_DIR/All-query-results-$DATETIME.txt 2>&1
