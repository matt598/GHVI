package main

import (
	"github.com/pressly/chi"
	"html/template"
	"net/http"
)

//go:generate go-bindata templates/

func getShelter(w http.ResponseWriter, r *http.Request) {
	runTemplate("templates/add.html", w, nil)
}

func fillBed(w http.ResponseWriter, r *http.Request)   {}
func unfillBed(w http.ResponseWriter, r *http.Request) {}

func getUpdateShelter(w http.ResponseWriter, r *http.Request)  {}
func postUpdateShelter(w http.ResponseWriter, r *http.Request) {}

func main() {
	r := chi.NewRouter()

	r.Route("/shelter", func(r chi.Router) {
		r.Get("/", getShelter)

		r.Post("/bed/fill", fillBed)
		r.Post("/bed/unfill", unfillBed)

		r.Route("/:shelterID", func(r chi.Router) {
			r.Get("/", getUpdateShelter)
			r.Post("/", postUpdateShelter)
		})
	})

	http.ListenAndServe("127.0.0.1:8080", r)
}

func runTemplate(name string, w http.ResponseWriter, data interface{}) {
	html, err := Asset(name)
	if err != nil {
		http.Error(w, http.StatusText(500), 500)
		return
	}

	t, err := template.New(name).Parse(string(html))
	if err != nil {
		http.Error(w, http.StatusText(500), 500)
		return
	}

	t.Execute(w, data)
}
