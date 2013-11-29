#!/bin/bash
# Assumes that the database name and password are dept in a secure directory
set -e
SQL_DIR="$HOME/mysql"
DB_NAME=`cat $SQL_DIR/db_name`
PASSWD=`cat $SQL_DIR/passwd`
SQL_REPO="$SQL_DIR/SCOOP-data-quality/PolypharmacySQLQueries"
cd $SQL_REPO
mysql -h 127.0.0.1 -P 3307 -u oscarb --database=$DB_NAME -vvv -t -AU --password=$PASSWD < All_queries.sql > $SQL_DIR/All-query-results.out 2>&1
