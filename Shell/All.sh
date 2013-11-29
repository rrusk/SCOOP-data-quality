#!/bin/bash
SQL_DIR="$HOME/mysql"
SQL_REPO="$SQL_DIR/SCOOP-data-quality/PolypharmacySQLQueries"
mysql -h 127.0.0.1 -P 3307 -u oscarb --database=`"$SQL_DIR"/db_name` -vvv -t -AU --password=`"$SQL_DIR"/passwd` < "$SQL_REPO"/All-queries.sql > All-query-results.out 2>&1
QP
