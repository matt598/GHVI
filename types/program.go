package types

var Programs = map[string][]int{
	"HUD: Continuum of Care Program (CoC)":                                []int{2, 3, 4, 6, 8, 9, 12, 13, 14},
	"HUD: Emergency Solutions Grant program (ESG)":                        []int{1, 4, 11, 12, 13, 14},
	"HUD: Rural Housing Stability Assitance Program (RHSAP)":              []int{},
	"HUD: Housing Opportunities for Persons with AIDS (HOPWA)":            []int{1, 2, 3, 6, 12},
	"HUD: Veterans Affairs Supportive Housing (HUD-VASH)":                 []int{3, 12},
	"HHS: Runaway and Homeless Youth Porgrams (RHY)":                      []int{1, 2, 4, 6, 12},
	"HHS: Projects for Assistance in Transition from Homelessness (PATH)": []int{4, 6},
	"VA: Grant and Per Diem Program (GPD)":                                []int{2},
	"VA: Supportive Services for Veteran Families (SSVF)":                 []int{12, 13},
	"VA: Community Contract Emergency Housing (HCHV/EH)":                  []int{1},
}

const (
	ProjectEmergencyShelter = 1
)
