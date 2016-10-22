package database

import (
	_ "github.com/go-sql-driver/mysql"
	"github.com/jmoiron/sqlx"
	"os"
)

var DB *sqlx.DB

func init() {
	DB = sqlx.MustOpen("mysql", os.Getenv("MYSQL_HOST"))
}
