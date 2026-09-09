export type Section = "reading_writing" | "math";
export type Difficulty = "easy" | "medium" | "hard" | "unrated";

export const SECTION_LABEL: Record<Section, string> = {
  reading_writing: "Reading & Writing",
  math: "Math",
};

export type SkillProgress = {
  skill_id: string;
  skill_code: string;
  skill_name: string;
  skill_order: number;
  domain_id: string;
  domain_code: string;
  domain_name: string;
  domain_order: number;
  section: Section;
  difficulty: Difficulty | null;
  total: number;
  solved: number;
};

export type Choice = {
  id: string;
  label: "A" | "B" | "C" | "D";
  content_md: string;
  is_graphic: boolean;
  asset_path: string | null;
  display_order: number;
};

export type Asset = {
  kind: string;
  role: "stimulus" | "choice";
  choice_label: string | null;
  storage_path: string;
  alt_text: string | null;
};

export type Question = {
  id: string;
  section: Section;
  question_type: "multiple_choice" | "grid_in";
  stimulus_md: string | null;
  prompt_md: string;
  has_figure: boolean;
  figure_alt_text: string | null;
  difficulty: Difficulty;
  test_number: number;
  module_number: number;
  question_number: number;
  skill_name: string;
  domain_name: string;
  choices: Choice[];
  assets: Asset[];
};
