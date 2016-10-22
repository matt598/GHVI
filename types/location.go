package types

type BedInventory struct {
	ChronicHomeless int
	Veteran         int
	YouthUnder18    int
	Youth18to24     int
	YouthUnder24    int
}

type Location struct {
	ProjectType int
	Bed         BedInventory
}
