#!/bin/bash
# Assumes that the database db_user, db_passwd, db_name and db_port are kept in a secure directory ~/mysql
set -e
DATETIME=`date +"%Y%m%d%H%M"`
SQL_DIR="$HOME/mysql/db_config"
DB_USER=`cat $SQL_DIR/db_user`
DB_NAME=`cat $SQL_DIR/db_name`
DB_PASSWD=`cat $SQL_DIR/db_passwd`
DB_PORT=`cat $SQL_DIR/db_port`
SQL_REPO="$SQL_DIR/SCOOP-data-quality/PolypharmacySQLQueries"
cd $SQL_REPO
mysql -h 127.0.0.1 -P $DB_PORT -u $DB_USER --database=$DB_NAME -n -vvv -t -AU --password=$DB_PASSWD \
    < All_queries.sql > $SQL_DIR/All-query-results-$DATETIME.txt 2>&1