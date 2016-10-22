package types

type Gender int

const (
	GenderFemale       = 0
	GenderMale         = 1
	GenderTransMTF     = 2
	GenderTransFTM     = 3
	GenderNotIdentify  = 4
	GenderUnknown      = 8
	GenderRefused      = 9
	GenderNotCollected = 99
)

func (g Gender) IsMale() bool {
	return g == GenderMale || g == GenderTransFTM
}

func (g Gender) IsFemale() bool {
	return g == GenderFemale || g == GenderTransMTF
}

func (g Gender) IsTrans() bool {
	return g == GenderTransFTM || g == GenderTransMTF
}

func (g Gender) IsOther() bool {
	return g == GenderNotIdentify || g == GenderUnknown
}

func NewGender(gender int) Gender {
	return Gender(gender)
}
