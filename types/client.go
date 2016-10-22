package types

import (
	"time"
)

type Client struct {
	DOB           *time.Time
	Gender        Gender
	VeteranStatus int
	Disability    int
	ChronicHealth int
	MentalHealth  int
	SubtanceAbuse int
	DomesticAbuse int
}
