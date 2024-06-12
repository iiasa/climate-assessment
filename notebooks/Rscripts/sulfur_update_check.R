# Visualising sulfur historical emissions of AR6 climate assessment workflow
# Do:
# - [x] visualise RCMIP (used in AR6)
# - [x] visualise CEDS 2024 update
# - [x] visualise difference between RCMIP and CEDS
# - [ ] write out Sulfur data from CEDS for global emissions


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


##### Save: SO2 emissions ------------------------------------------------------
ceds.emssions.sulfur.wide <- ceds.emssions.sulfur %>% pivot_wider(names_from = Year, values_from = value)

write_delim(
  x = ceds.emssions.sulfur.wide,
  file = here("notebooks", "Rscripts", "output-data", "sulfur_emissions_CEDS_global.csv"),
  delim = ","
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


### AR6 Metadata ---------------------------------------------------------------
ar6.metadata <- readxl::read_excel(
  "C:/Users/kikstra/OneDrive - IIASA/_Other/Data/Scenario data/Scenario Databases/AR6_Scenarios_Database_World_v1.1/AR6_Scenarios_Database_metadata_indicators_v1.1.xlsx",
  sheet = "meta_Ch3vetted_withclimate"
) %>% select(Model,Scenario,Category)



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
  geom_line(linewidth=1.5) +
  geom_line(data = sulfur.scens.ar6 %>% filter(Year>=2015,Year<=2050),
                aes(x=Year, y=value, group=interaction(Model,Scenario)),
                colour = "grey",
                linetype = "solid", alpha = 0.1) +
  geom_line(data = sulfur.scens.ar6 %>% filter(Year>=2015,Year<=2050) %>%
              left_join(ar6.metadata) %>%
              filter(Category=="C1"),
            aes(x=Year, y=value, group=interaction(Model,Scenario)),
            colour = "dodgerblue",
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
    subtitle = "Grey: harmonized emissions AR6,\nLight blue: C1 scenarios",
    x = "Year",
    y = "Emissions (Mt SO2/yr)"
  ) +
  theme_minimal()
p.sulfur.scens

ggsave(filename = here("notebooks", "Rscripts", "figures", "sulfur_emissions.pdf"),
       plot = p.sulfur.scens, device = cairo_pdf,
       width = 300, height = 200, dpi = 300, units = "mm")
ggsave(filename = here("notebooks", "Rscripts", "figures", "sulfur_emissions.png"),
       plot = p.sulfur.scens,
       width = 300, height = 200, dpi = 300, units = "mm")



# Visualisation (historical emissions difference) ------------------------------
sulfur.hist.diff <- rcmip.emssions %>% filter(grepl(Variable,pattern="Sulfur",fixed=T)) %>%
  mutate(Variable = "Sulfur (historical, AR6, RCMIP)") %>%
  bind_rows(ceds.emssions.sulfur) %>%
  select(Variable,Unit,Year,value) %>%
  pivot_wider(names_from = Variable, values_from = value) %>%
  mutate(diff = `SO2 (CEDS, Jan 2024 update)` - `Sulfur (historical, AR6, RCMIP)`) %>%
  mutate(diff.rel.to.rcmip = diff / `Sulfur (historical, AR6, RCMIP)`)


p.sulfur.hist.diff <- ggplot(sulfur.hist.diff %>% filter(Year >= 1970),
                        aes(x=Year, y=diff.rel.to.rcmip)) +
  geom_line() +
  geom_hline(yintercept = 0, linetype = "dashed") +
  labs(
    title = "Historical sulfur emissions (difference)",
    x = "Year",
    y = "% difference from AR6"
  ) +
  # scale y axis to percentages
  scale_y_continuous(labels = scales::percent) +
  theme_minimal()
p.sulfur.hist.diff

ggsave(filename = here("notebooks", "Rscripts", "figures", "sulfur_emissions_hist_diff.pdf"),
       plot = p.sulfur.hist.diff, device = cairo_pdf,
       width = 200, height = 100, dpi = 300, units = "mm")
ggsave(filename = here("notebooks", "Rscripts", "figures", "sulfur_emissions_hist_diff.png"),
       plot = p.sulfur.hist.diff,
       width = 200, height = 100, dpi = 300, units = "mm")




# Create new CMIP6 emissions dataset (all vetted scenarios) --------------------
ar6.data.location.global <- "C:/Users/kikstra/OneDrive - IIASA/_Other/Data/Scenario data/Scenario Databases/AR6_Scenarios_Database_World_v1.1"
ar6.data.file.global <- "AR6_Scenarios_Database_World_v1.1.csv"
ar6.meta.file <- "AR6_Scenarios_Database_metadata_indicators_v1.1.xlsx"

ar6.meta <- read_excel(file.path(ar6.data.location.global, ar6.meta.file),
                       sheet = "meta"
                       # sheet = "meta_Ch3vetted_withclimate"
                       ) %>%
  select(Model, Scenario,
         Category) %>%
  filter(Category!="failed-vetting")

ar6.data.emissions <- vroom(
  file.path(
    ar6.data.location.global,
    ar6.data.file.global
  )
) %>%
  left_join(ar6.meta) %>%
  drop_na(Category) %>% select(-Category) %>%
  filter(str_detect(Variable, "^Emissions")) # in regex, the ^ symbol indicates the beginning of a string

write_delim(
  x = ar6.data.emissions,
  file = here("notebooks", "Rscripts", "output-data", "ar6_emissions_vettedscenarios.csv"),
  delim = ",",
  na = ""
)








# Create new CMIP6 emissions dataset (all vetted scenarios) --------------------
ar6.inf.emssions.newCEDSso2 <- read_csv(here("output",
                                  "ar6_emissions_vettedscenarios_harmonized.csv")) %>%
  pivot_longer(cols = -c(Model,Scenario,Region,Variable,Unit),
               names_to = "Year",
               values_to = "value") %>%
  mutate(Year = as.numeric(Year))

### new harmonized emissions (for infiller database) ---------------------------
sulfur.scens.cmip6 <- cmip6.emssions %>% filter(grepl(Variable,pattern="Sulfur",fixed=T)) %>%
  mutate(Variable = "Emissions|Sulfur (future, CMIP6)")
sulfur.scens.ar6.newCEDSso2 <- ar6.inf.emssions.newCEDSso2 %>% filter(grepl(Variable,pattern="Sulfur",fixed=T)) %>%
  mutate(Variable = "Emissions|Sulfur (future, AR6 infiller database)")

p.sulfur.scens.newCEDSso2 <- ggplot(sulfur.hist %>% filter(Year >= 1990),
                         aes(x=Year, y=value, color=Variable)) +
  geom_line(linewidth=1.5) +
  geom_line(data = sulfur.scens.ar6.newCEDSso2 %>% filter(Year>=2015,Year<=2050),
            aes(x=Year, y=value, group=interaction(Model,Scenario)),
            colour = "grey",
            linetype = "solid", alpha = 0.1) +
  geom_line(data = sulfur.scens.ar6.newCEDSso2 %>% filter(Year>=2015,Year<=2050) %>%
              left_join(ar6.metadata) %>%
              filter(Category=="C1"),
            aes(x=Year, y=value, group=interaction(Model,Scenario)),
            colour = "dodgerblue",
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
    subtitle = "Grey: harmonized emissions AR6,\nLight blue: C1 scenarios",
    x = "Year",
    y = "Emissions (Mt SO2/yr)"
  ) +
  theme_minimal()
p.sulfur.scens.newCEDSso2

ggsave(filename = here("notebooks", "Rscripts", "figures", "sulfur_emissions_newCEDSso2.pdf"),
       plot = p.sulfur.scens.newCEDSso2, device = cairo_pdf,
       width = 300, height = 200, dpi = 300, units = "mm")
ggsave(filename = here("notebooks", "Rscripts", "figures", "sulfur_emissions_newCEDSso2.png"),
       plot = p.sulfur.scens.newCEDSso2,
       width = 300, height = 200, dpi = 300, units = "mm")
