package main

import (
	"context"
	"database/sql"
	_ "github.com/go-sql-driver/mysql"
	"github.com/jmoiron/sqlx"
	"github.com/pressly/chi"
	"github.com/pressly/chi/middleware"
	"googlemaps.github.io/maps"
	"html/template"
	"net/http"
	"os"
	"strconv"
)

var DB *sqlx.DB

type Shelter struct {
	ID            int64         `db:"id"`
	Name          string        `db:"name"`
	Address       string        `db:"address"`
	Latitude      float64       `db:"latitude"`
	Longitude     float64       `db:"longitude"`
	BedsAvailable int           `db:"beds_available"`
	BedsFull      int           `db:"beds_full"`
	MinAge        sql.NullInt64 `db:"min_age"`
	MaxAge        sql.NullInt64 `db:"max_age"`
	AllowMale     bool          `db:"allow_male"`
	AllowFemale   bool          `db:"allow_female"`
	AllowTrans    bool          `db:"allow_trans"`
	Disability    int           `db:"disability"`
	Dependent     int           `db:"dependent"`
	Abuse         bool          `db:"abuse"`
	Veteran       bool          `db:"veteran"`
}

//go:generate go-bindata templates/

func getShelter(w http.ResponseWriter, r *http.Request) {
	runTemplate("templates/add.html", w, nil)
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

func postShelter(w http.ResponseWriter, r *http.Request) {
	r.ParseForm()

	c, err := maps.NewClient(maps.WithAPIKey(os.Getenv("GOOGLEMAPS_API")))
	if err != nil {
		panic(err)
	}
	req := &maps.GeocodingRequest{
		Address: getFormValue(r, "address"),
	}
	resp, err := c.Geocode(context.Background(), req)
	if err != nil {
		panic(err)
	}
	loc := resp[0].Geometry.Location

	DB.MustExec(`insert into shelter (
		name,
		address,
		latitude,
		longitude,
		beds_available,
		min_age,
		max_age,
		allow_male,
		allow_female,
		allow_trans,
		disability,
		dependent,
		abuse,
		veteran) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		getFormValue(r, "name"),
		getFormValue(r, "address"),
		loc.Lat,
		loc.Lng,
		getFormValue(r, "beds_available"),
		getFormValueWithDefault(r, "min_age", nil),
		getFormValueWithDefault(r, "max_age", nil),
		getFormValueWithDefault(r, "allow_male", true),
		getFormValueWithDefault(r, "allow_female", true),
		getFormValueWithDefault(r, "allow_trans", true),
		getFormValueWithDefault(r, "disability", 2),
		getFormValueWithDefault(r, "dependent", 2),
		getFormValueWithDefault(r, "abuse", false),
		getFormValueWithDefault(r, "veteran", false),
	)
}

func fillBed(w http.ResponseWriter, r *http.Request) {
	shelter := r.Context().Value("shelter").(Shelter)

	if shelter.BedsAvailable == shelter.BedsFull {
		http.Error(w, http.StatusText(406), 406)
		return
	}

	DB.Exec(`update shelter set beds_full = beds_full + 1`)

	http.Redirect(w, r, "/shelter/"+strconv.FormatInt(shelter.ID, 10), 302)
}

func unfillBed(w http.ResponseWriter, r *http.Request) {
	shelter := r.Context().Value("shelter").(Shelter)

	if shelter.BedsFull == 0 {
		http.Error(w, http.StatusText(406), 406)
		return
	}

	DB.Exec(`update shelter set beds_full = beds_full - 1`)

	http.Redirect(w, r, "/shelter/"+strconv.FormatInt(shelter.ID, 10), 302)
}

func setBed(w http.ResponseWriter, r *http.Request) {
	shelter := r.Context().Value("shelter").(Shelter)
	r.ParseForm()

	val := r.Form["value"][0]
	parsed, _ := strconv.ParseInt(val, 10, 64)
	if parsed < 0 || parsed > int64(shelter.BedsAvailable) {
		http.Error(w, http.StatusText(406), 406)
		return
	}

	DB.Exec(`update shelter set beds_full = ?`, parsed)

	http.Redirect(w, r, "/shelter/"+strconv.FormatInt(shelter.ID, 10), 302)
}

func getUpdateShelter(w http.ResponseWriter, r *http.Request) {
	runTemplate("templates/shelter.html", w, struct{ Shelter Shelter }{r.Context().Value("shelter").(Shelter)})
}

func postUpdateShelter(w http.ResponseWriter, r *http.Request) {}

func main() {
	r := chi.NewRouter()

	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	DB = sqlx.MustOpen("mysql", "root:@/gh6")

	r.Get("/", nil)

	r.Route("/shelter", func(r chi.Router) {
		r.Get("/", getShelter)
		r.Post("/", postShelter)

		r.Route("/:shelterID", func(r chi.Router) {
			r.Use(ShelterCtx)

			r.Get("/", getUpdateShelter)
			r.Post("/", postUpdateShelter)

			r.Post("/bed/fill", fillBed)
			r.Post("/bed/unfill", unfillBed)
			r.Post("/bed/set", setBed)
		})
	})

	http.ListenAndServe("127.0.0.1:8080", r)
}

func ShelterCtx(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		itemID := chi.URLParam(r, "shelterID")

		var shelter Shelter
		err := DB.Get(&shelter, `SELECT * FROM shelter WHERE id = ?`, itemID)
		if err != nil {
			http.Error(w, http.StatusText(404), 404)
			return
		}

		ctx := context.WithValue(r.Context(), "shelter", shelter)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
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
