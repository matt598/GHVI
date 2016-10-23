package shelter

import (
	"context"
	"database/sql"
	"github.com/pressly/chi"
	"googlemaps.github.io/maps"
	"html/template"
	"net/http"
	"os"
	"strconv"

	"github.com/ixchi/gh6/database"
)

type Shelter struct {
	ID            int64         `db:"id"`
	Name          string        `db:"name"`
	Phone         string        `db:"phone"`
	Email         string        `db:"email"`
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

	Distance *float32 `db:"distance"`
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

	q := database.DB.MustExec(`insert into shelter (
		name,
		address,
		phone,
		email,
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
		veteran) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		getFormValue(r, "name"),
		getFormValue(r, "address"),
		getFormValue(r, "phone"),
		getFormValue(r, "email"),
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
	id, _ := q.LastInsertId()

	http.Redirect(w, r, "/shelter/"+strconv.FormatInt(id, 10), 302)
}

func fillBed(w http.ResponseWriter, r *http.Request) {
	shelter := r.Context().Value("shelter").(Shelter)

	if shelter.BedsAvailable == shelter.BedsFull {
		http.Error(w, http.StatusText(406), 406)
		return
	}

	database.DB.Exec(`update shelter set beds_full = beds_full + 1 where id = ?`, shelter.ID)

	http.Redirect(w, r, "/shelter/"+strconv.FormatInt(shelter.ID, 10), 302)
}

func unfillBed(w http.ResponseWriter, r *http.Request) {
	shelter := r.Context().Value("shelter").(Shelter)

	if shelter.BedsFull == 0 {
		http.Error(w, http.StatusText(406), 406)
		return
	}

	database.DB.Exec(`update shelter set beds_full = beds_full - 1 where id = ?`, shelter.ID)

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

	database.DB.Exec(`update shelter set beds_full = ? where id = ?`, parsed, shelter.ID)

	http.Redirect(w, r, "/shelter/"+strconv.FormatInt(shelter.ID, 10), 302)
}

func getUpdateShelter(w http.ResponseWriter, r *http.Request) {
	runTemplate("templates/shelter.html", w, struct{ Shelter Shelter }{r.Context().Value("shelter").(Shelter)})
}

func postUpdateShelter(w http.ResponseWriter, r *http.Request) {}

func getLocation(w http.ResponseWriter, r *http.Request) {
	runTemplate("templates/address.html", w, nil)
}

func listShelters(w http.ResponseWriter, r *http.Request) {
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

	var shelters []Shelter
	err = database.DB.Select(&shelters, `
		SELECT *, round(haversine(shelter.latitude, shelter.longitude, ?, ?) * 0.621371, 2) distance
		FROM shelter
		ORDER BY distance ASC
		LIMIT 10
	`, loc.Lat, loc.Lng)

	runTemplate("templates/list.html", w, struct {
		Shelters []Shelter
	}{shelters})
}

func GetRouter() http.Handler {
	r := chi.NewRouter()

	r.Get("/", getShelter)
	r.Post("/", postShelter)

	r.Get("/list", getLocation)
	r.Post("/list", listShelters)

	r.Route("/:shelterID", func(r chi.Router) {
		r.Use(ShelterCtx)

		r.Get("/", getUpdateShelter)
		r.Post("/", postUpdateShelter)

		r.Post("/bed/fill", fillBed)
		r.Post("/bed/unfill", unfillBed)
		r.Post("/bed/set", setBed)
	})

	return r
}

func ShelterCtx(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		itemID := chi.URLParam(r, "shelterID")

		var shelter Shelter
		err := database.DB.Get(&shelter, `SELECT * FROM shelter WHERE id = ?`, itemID)
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
