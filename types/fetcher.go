package types

type Fetcher interface {
	GetLocation() (Location, error)
}
