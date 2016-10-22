package main

import (
	"github.com/pressly/chi"
	"github.com/pressly/chi/middleware"
	"net/http"

	"github.com/ixchi/gh6/client"
	"github.com/ixchi/gh6/shelter"
)

func main() {
	r := chi.NewRouter()

	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	r.Mount("/shelter", shelter.GetRouter())
	r.Mount("/client", client.GetRouter())

	http.ListenAndServe("127.0.0.1:8080", r)
}
