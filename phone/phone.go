package phone

import (
	"bytes"
	"encoding/json"
	"errors"
	"github.com/pressly/chi"
	"net/http"
)

func GetRouter() http.Handler {
	r := chi.NewRouter()

	return r
}
