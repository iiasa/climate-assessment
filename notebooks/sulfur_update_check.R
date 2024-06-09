# Visualising sulfur historical emissions of AR6 climate assessment workflow
# Do:
# - [ ] visualise RCMIP (used in AR6)
# - [ ] visualise CEDS 2024 update


library(tidyverse)
library(geomtextpath)
library(here)
try(setwd(dirname(rstudioapi::getActiveDocumentContext()$path)))
here::i_am("README.rst")

# Data -------------------------------------------------------------------------

### RCMIP ----------------------------------------------------------------------
rcmip.emssions <- read_csv(here("src", 
                                "climate_assessment",
                                "harmonization",
                                "history_ar6.csv")) %>% 
  pivot_longer(cols = -c(Model,Scenario,Region,Variable,Unit),
               names_to = "Year",
               values_to = "value") %>% 
  mutate(Year = as.numeric(Year))

### CEDS 2024 ------------------------------------------------------------------
# [ ] move file to climate-assessment folder if we start using it
##### SO2 ----------------------------------------------------------------------
ceds.emssions.sulfur <- read_csv(
  "C:/Users/kikstra/OneDrive - IIASA/_Other/Data/Emissions data/CEDS/CEDS_v_2024_04_01_aggregate/SO2_CEDS_emissions_by_country_v2024_04_01.csv"
) %>% 
  pivot_longer(cols = -c(em,country,units),
               names_to = "Year",
               values_to = "value") %>% 
  mutate(Year = as.numeric(substr(Year, 2, 5))) %>% 
  summarise(
    value = sum(value, na.rm = TRUE)*1e3/1e6,
    Unit = "Mt SO2/yr",
    Variable = "SO2 (CEDS, Jan 2024 update)",
    .by = c("Year")
  )



### Future emissions (CMIP6) ---------------------------------------------------
cmip6.emssions <- read_csv(here("src", 
                                "climate_assessment",
                                "infilling",
                                "cmip6-ssps-workflow-emissions.csv")) %>% 
  pivot_longer(cols = -c(Model,Scenario,Region,Variable,Unit),
               names_to = "Year",
               values_to = "value") %>% 
  mutate(Year = as.numeric(Year))

### Future emissions (Infiller database AR6) -----------------------------------
ar6.inf.emssions <- read_csv(here("tests", 
                                "test-data",
                                "ar6_vetted_infillerdatabase.csv")) %>% 
  pivot_longer(cols = -c(Model,Scenario,Region,Variable,Unit),
               names_to = "Year",
               values_to = "value") %>% 
  mutate(Year = as.numeric(Year))


# Visualisation (historical emissions) -----------------------------------------

### Sulfur ---------------------------------------------------------------------
sulfur.hist <- rcmip.emssions %>% filter(grepl(Variable,pattern="Sulfur",fixed=T)) %>%
  mutate(Variable = "Sulfur (historical, AR6, RCMIP)") %>%
  bind_rows(ceds.emssions.sulfur)

p.sulfur.hist <- ggplot(sulfur.hist %>% filter(Year >= 1970), 
                        aes(x=Year, y=value, color=Variable)) +
  geom_line() +
  geom_hline(yintercept = 0, linetype = "dashed") +
  labs(
    title = "Historical sulfur emissions",
    x = "Year",
    y = "Emissions (Mt SO2/yr)"
  ) +
  theme_minimal()
p.sulfur.hist


# Visualisation (future emissions) ---------------------------------------------

### Sulfur ---------------------------------------------------------------------
sulfur.scens.cmip6 <- cmip6.emssions %>% filter(grepl(Variable,pattern="Sulfur",fixed=T)) %>%
  mutate(Variable = "Emissions|Sulfur (future, CMIP6)")
sulfur.scens.ar6 <- ar6.inf.emssions %>% filter(grepl(Variable,pattern="Sulfur",fixed=T)) %>%
  mutate(Variable = "Emissions|Sulfur (future, AR6 infiller database)")

p.sulfur.scens <- ggplot(sulfur.hist %>% filter(Year >= 1990), 
                        aes(x=Year, y=value, color=Variable)) +
  geom_line() +
  geom_line(data = sulfur.scens.ar6 %>% filter(Year>=2015,Year<=2050), 
                aes(x=Year, y=value, group=interaction(Model,Scenario)),
                colour = "grey",
                linetype = "solid", alpha = 0.1) +
  geom_textline(data = sulfur.scens.cmip6 %>% filter(Year>=2015,Year<=2050), 
                aes(x=Year, y=value, group=interaction(Model,Scenario), label = Scenario), 
                linetype = "dashed",
                colour = "black",
                hjust=0.9) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  scale_color_manual(values = c("blue", "red")) +
  labs(
    title = "Historical sulfur emissions",
    x = "Year",
    y = "Emissions (Mt SO2/yr)"
  ) +
  theme_minimal()
p.sulfur.scens

ggsave(filename = here("notebooks", "Rscripts", "figures", "sulfur_emissions.pdf"), 
       plot = p.sulfur.scens, device = cairo_pdf,
       width = 300, height = 200, dpi = 300, units = "mm")
