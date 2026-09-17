import { describe, expect, test } from "bun:test";
import { cleanMemberName, cleanTeamName, cleanUserId, generateTeamId } from "../src/domain/utility";

describe("cleanMemberName", () => {
  test("title-cases and collapses double spaces", () => {
    expect(cleanMemberName("  kevin  conley ")).toBe("Kevin Conley");
  });

  test("applies known aliases after cleaning", () => {
    expect(cleanMemberName("joe guidoboni")).toBe("Joe");
    expect(cleanMemberName("Brendan Shea")).toBe("Durgan");
  });

  test("title-cases names with apostrophes like Python's str.title()", () => {
    expect(cleanMemberName("mary o'brien")).toBe("Mary O'Brien");
  });
});

describe("cleanTeamName", () => {
  test("trims and collapses double spaces", () => {
    expect(cleanTeamName("Kevin Conley", 2020, "  The   Koins  ")).toBe("The  Koins");
  });

  test("redacts team names for the configured owner/year pairs", () => {
    expect(cleanTeamName("Billy Heanue", 2017, "Some Team")).toBe("Redacted");
    expect(cleanTeamName("Billy Heanue", 2018, "Some Team")).toBe("Redacted");
    expect(cleanTeamName("Billy Heanue", 2019, "Some Team")).toBe("Some Team");
  });
});

describe("cleanUserId", () => {
  test("strips quotes and braces", () => {
    expect(cleanUserId("'{ABC-123}'")).toBe("ABC-123");
  });

  test("maps known duplicate ids", () => {
    expect(cleanUserId("{7B1424F4-143B-4EB5-BA40-08B7A978921F}")).toBe(
      "BC7D0741-6090-4ABA-9F23-1590DCDC6434",
    );
  });
});

describe("generateTeamId", () => {
  test("is deterministic and distinguishes by year", () => {
    expect(generateTeamId(1, 2020)).toBe(generateTeamId(1, 2020));
    expect(generateTeamId(1, 2020)).not.toBe(generateTeamId(1, 2021));
    expect(generateTeamId(1, 2020)).not.toBe(generateTeamId(2, 2020));
  });
});
