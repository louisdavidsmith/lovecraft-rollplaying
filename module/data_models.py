from typing import List, Optional

from pydantic import BaseModel


class PlayerCharacter(BaseModel):
    name: str
    profession: str
    age: Optional[int]
    hair_color: str
    description: str
    gender: str


class CharacterData(BaseModel):
    name: str
    adventure_name: str
    sanity: int
    physical: int
    wits: int
    social: int
    composure: int


class NonPlayerCharacter(BaseModel):
    name: str
    profession: str
    description: str
    hair_color: str
    gender: str
    role: str


class Location(BaseModel):
    name: str
    description: str


class Event(BaseModel):
    description: str


class Scenario(BaseModel):
    premise: str
    protaganist: PlayerCharacter
    non_player_characters: List[NonPlayerCharacter]
    locations: List[Location]
    events: List[Event]
