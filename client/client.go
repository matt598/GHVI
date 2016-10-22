package client

import (
	"context"
	"github.com/ixchi/gh6/database"
	"github.com/pressly/chi"
	"html/template"
	"log"
	"net/http"
	"strconv"
	"time"
)

//go:generate go-bindata templates/

type Client struct {
}

func getClient(w http.ResponseWriter, r *http.Request) {
	var months []string
	for i := time.January; i <= time.December; i++ {
		months = append(months, i.String())
	}
	var years []string
	for i := time.Now().Year(); i >= 1900; i-- {
		years = append(years, strconv.Itoa(i))
	}
	var days []string
	for i := 1; i <= 31; i++ {
		days = append(days, strconv.Itoa(i))
	}
	runTemplate("templates/form.html", w, struct {
		Months []string
		Years  []string
		Days   []string
	}{months, years, days})
}

func getFormValue(r *http.Request, key string) string {
	if val, ok := r.Form[key]; ok && len(val) == 1 {
		return val[0]
	}
	return ""
}

func getFormValueWithDefault(r *http.Request, key string, d interface{}) interface{} {
	if val, ok := r.Form[key]; ok && len(val) == 1 && val[0] != "" {
		return val[0]
	}
	return d
}

func postClient(w http.ResponseWriter, r *http.Request) {
	r.ParseForm()

	year, _ := strconv.Atoi(getFormValue(r, "year"))
	month, _ := strconv.Atoi(getFormValue(r, "month"))
	day, _ := strconv.Atoi(getFormValue(r, "day"))

	date := time.Date(year, time.Month(month), day, 0, 0, 0, 0, time.UTC)

	_, err := database.DB.Exec(`insert into client (
		dob,
		gender,
		dependents,
		veteran,
		disability,
		chronic,
		mental,
		substance,
		domestic
	) values (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		date,
		getFormValue(r, "gender"),
		getFormValueWithDefault(r, "dependents", nil) == "on",
		getFormValueWithDefault(r, "veteran", nil) == "on",
		getFormValueWithDefault(r, "disability", nil) == "on",
		getFormValueWithDefault(r, "chronic", nil) == "on",
		getFormValueWithDefault(r, "mental", nil) == "on",
		getFormValueWithDefault(r, "substance", nil) == "on",
		getFormValueWithDefault(r, "domestic", nil) == "on",
	)

	if err != nil {
		log.Println(err)
		http.Error(w, http.StatusText(500), 500)
		return
	}

	http.Error(w, http.StatusText(200), 200)
}

func GetRouter() http.Handler {
	r := chi.NewRouter()

	r.Get("/", getClient)
	r.Post("/", postClient)

	return r
}

func runTemplate(name string, w http.ResponseWriter, data interface{}) {
	html, err := Asset(name)
	if err != nil {
		http.Error(w, http.StatusText(500), 500)
		return
	}

	funcMap := template.FuncMap{
		"inc": func(i int) int {
			return i + 1
		},
	}

	t, err := template.New(name).Funcs(funcMap).Parse(string(html))
	if err != nil {
		http.Error(w, http.StatusText(500), 500)
		return
	}

	t.Execute(w, data)
}

func ClientCtx(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		itemID := chi.URLParam(r, "clientID")

		var client Client
		err := database.DB.Get(&client, `SELECT * FROM client WHERE id = ?`, itemID)
		if err != nil {
			http.Error(w, http.StatusText(404), 404)
			return
		}

		ctx := context.WithValue(r.Context(), "client", client)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}
