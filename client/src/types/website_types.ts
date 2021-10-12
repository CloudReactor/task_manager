export interface UserAccessLevel {
  user: {
    username: string,
    email: string,
  },
  access_level: number;
}

export interface Group {
  id: number;
  name: string;
  user_access_levels?: UserAccessLevel[]
}

export interface UserBase {
  username: string;
  first_name?: string;
  last_name?: string;
  email: string;
}

export interface UserProfile {

}

export interface User extends UserBase {
  id: number;
  date_joined: Date;
  groups: Group[];
  user_profile: UserProfile;
  group_access_levels: { [groupId: string]: number }
}

export interface UserRegistration extends UserBase {
  password: string;
}

export interface Invitation {
  to_email: string;
  invited_by_user: UserBase;
  group: Group;
  group_access_level: number | null;
  accepted_at: Date | null;
}