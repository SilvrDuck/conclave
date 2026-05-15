import { z } from "zod";
import { getJson } from "./client";

const memberStatus = z.enum(["proposed", "admitted", "exiled"]);
const agendaSection = z.enum(["doing", "next", "blocked_on"]);

export const MemberSchema = z.object({
  name: z.string(),
  status: memberStatus,
  charter_path: z.string(),
  admitted_at: z.string().nullable().optional(),
  exiled_at: z.string().nullable().optional(),
});

export const EndpointSchema = z.object({
  pod: z.string(),
  method: z.string(),
  path: z.string(),
  annotation: z.string().nullable().optional(),
  first_seen: z.string(),
  last_seen: z.string(),
});

export const AgendaItemSchema = z.object({
  id: z.string(),
  pod: z.string(),
  section: agendaSection,
  text: z.string(),
  since: z.string().nullable().optional(),
  eta: z.string().nullable().optional(),
  updated_at: z.string(),
});

export const AgendaSnapshotSchema = z.object({
  pod: z.string(),
  doing: z.array(AgendaItemSchema),
  next: z.array(AgendaItemSchema),
  blocked_on: z.array(AgendaItemSchema),
  updated_at: z.string(),
});

export const ChatroomSchema = z.object({
  id: z.string(),
  topic: z.string(),
  participants: z.array(z.string()),
  opened_by: z.string(),
  opened_at: z.string(),
  last_active: z.string(),
  closed_at: z.string().nullable().optional(),
  summary: z.string().nullable().optional(),
});

const MembersOut = z.object({ members: z.array(MemberSchema) });
const EndpointsOut = z.object({ endpoints: z.array(EndpointSchema) });
const ChatroomsOut = z.object({ chatrooms: z.array(ChatroomSchema) });
const AgendaOut = z.object({ snapshot: AgendaSnapshotSchema });
const CallersOut = z.object({ callers: z.array(z.string()) });

export type Member = z.infer<typeof MemberSchema>;
export type Endpoint = z.infer<typeof EndpointSchema>;
export type AgendaItem = z.infer<typeof AgendaItemSchema>;
export type AgendaSnapshot = z.infer<typeof AgendaSnapshotSchema>;
export type Chatroom = z.infer<typeof ChatroomSchema>;
export type MemberStatus = z.infer<typeof memberStatus>;

export async function listMembers(): Promise<Member[]> {
  const data = await getJson("/state/members");
  return MembersOut.parse(data).members;
}

export async function listEndpoints(pod: string): Promise<Endpoint[]> {
  const data = await getJson(`/state/endpoints/${encodeURIComponent(pod)}`);
  return EndpointsOut.parse(data).endpoints;
}

export async function listCallers(
  method: string,
  path: string,
): Promise<string[]> {
  const qs = new URLSearchParams({ method, path }).toString();
  const data = await getJson(`/state/callers?${qs}`);
  return CallersOut.parse(data).callers;
}

export async function listChatrooms(): Promise<Chatroom[]> {
  const data = await getJson("/state/chatrooms");
  return ChatroomsOut.parse(data).chatrooms;
}

export async function getAgenda(pod: string): Promise<AgendaSnapshot> {
  const data = await getJson(`/state/agenda/${encodeURIComponent(pod)}`);
  return AgendaOut.parse(data).snapshot;
}
