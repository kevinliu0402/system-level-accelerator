/////////////////////////////////////////////////////////////////////////
//  Reorder Buffer (Active List) — dispatch / complete / commit / squash
//
//  Kevin Liu — Milestone 2: in-order commit, OoO completion, branch-safe
//  flush by rolling tail, exception flags on commit.
/////////////////////////////////////////////////////////////////////////

`include "verilog/sys_defs.svh"

module rob (
    input logic clock,
    input logic reset,

    // --- Dispatch (rename allocates one ROB slot) ---
    input logic disp_en,
    input logic [4:0] disp_arch_dest,
    input logic disp_has_dest,
    input logic [`XLEN-1:0] disp_NPC,
    output logic disp_ready,
    output logic [$clog2(`ROB_SZ)-1:0] disp_rob_tag,

    // --- Single completion port (widen later for superscalar `N` > 1) ---
    input logic cplt_en,
    input logic [$clog2(`ROB_SZ)-1:0] cplt_tag,
    input logic [`XLEN-1:0] cplt_value,
    input logic cplt_illegal,
    input logic cplt_halt,

    // --- Squash wrong-path uops: clears [squash_from, tail) and sets tail ---
    input logic squash_en,
    input logic [$clog2(`ROB_SZ)-1:0] squash_from,

    // --- In-order commit (head), one uop per cycle when `N==1` ---
    output logic rob_commit_valid,
    output logic [4:0] rob_commit_arch_dest,
    output logic rob_commit_has_dest,
    output logic [`XLEN-1:0] rob_commit_value,
    output logic rob_commit_wr_en,
    output logic rob_commit_illegal,
    output logic rob_commit_halt,
    output logic [`XLEN-1:0] rob_commit_NPC,

    output logic rob_empty,
    output EXCEPTION_CODE rob_exception_status
);

    localparam int TAG_W = $clog2(`ROB_SZ);

    typedef struct packed {
        logic valid;
        logic ready;
        logic [4:0] arch_dest;
        logic has_dest;
        logic [`XLEN-1:0] result;
        logic [`XLEN-1:0] NPC;
        logic illegal;
        logic halt;
    } rob_entry_t;

    rob_entry_t entries[`ROB_SZ-1:0];

    logic [TAG_W-1:0] head;
    logic [TAG_W-1:0] tail;

    function automatic logic rob_in_range(
        logic [TAG_W-1:0] idx,
        logic [TAG_W-1:0] lo_incl,
        logic [TAG_W-1:0] hi_excl
    );
        if (lo_incl == hi_excl)
            return 1'b0;
        if (lo_incl < hi_excl)
            return (idx >= lo_incl) && (idx < hi_excl);
        return (idx >= lo_incl) || (idx < hi_excl);
    endfunction

    function automatic logic [TAG_W-1:0] rob_inc(logic [TAG_W-1:0] x);
        return (x == TAG_W'(`ROB_SZ - 1)) ? '0 : x + 1'b1;
    endfunction

    wire rob_full = (rob_inc(tail) == head);
    assign disp_ready = ~rob_full;

    assign rob_empty = (head == tail);

    wire head_valid_ready = entries[head].valid & entries[head].ready;

    assign rob_commit_valid     = head_valid_ready;
    assign rob_commit_arch_dest = entries[head].arch_dest;
    assign rob_commit_has_dest  = entries[head].has_dest;
    assign rob_commit_value     = entries[head].result;
    assign rob_commit_illegal   = entries[head].illegal;
    assign rob_commit_halt      = entries[head].halt;
    assign rob_commit_NPC       = entries[head].NPC;
    assign rob_commit_wr_en     = head_valid_ready & entries[head].has_dest
        & ~entries[head].illegal & ~entries[head].halt;

    assign rob_exception_status = !head_valid_ready ? NO_ERROR :
        entries[head].illegal ? ILLEGAL_INST :
        entries[head].halt ? HALTED_ON_WFI : NO_ERROR;

    integer ri;

    always_ff @(posedge clock) begin
        if (reset) begin
            head <= '0;
            tail <= '0;
            disp_rob_tag <= '0;
            for (ri = 0; ri < `ROB_SZ; ri++) begin
                entries[ri].valid <= 1'b0;
                entries[ri].ready <= 1'b0;
                entries[ri].arch_dest <= '0;
                entries[ri].has_dest <= 1'b0;
                entries[ri].result <= '0;
                entries[ri].NPC <= '0;
                entries[ri].illegal <= 1'b0;
                entries[ri].halt <= 1'b0;
            end
        end else begin
            automatic logic [TAG_W-1:0] H;
            automatic logic [TAG_W-1:0] T;
            automatic logic [TAG_W-1:0] tail_before_squash;

            H = head;
            T = tail;
            tail_before_squash = tail;

            // 1) Retire at head
            if (entries[H].valid & entries[H].ready) begin
                entries[H].valid   <= 1'b0;
                entries[H].ready   <= 1'b0;
                entries[H].illegal <= 1'b0;
                entries[H].halt    <= 1'b0;
                H = rob_inc(H);
            end

            head <= H;

            // 2) Squash wrong-path slots
            if (squash_en) begin
                for (ri = 0; ri < `ROB_SZ; ri++) begin
                    if (rob_in_range(TAG_W'(ri), squash_from, tail_before_squash)) begin
                        entries[ri].valid <= 1'b0;
                        entries[ri].ready <= 1'b0;
                    end
                end
                T = squash_from;
            end

            // 3) Completion (drop if this tag is squashed this cycle)
            if (cplt_en && entries[cplt_tag].valid &&
                    !(squash_en && rob_in_range(cplt_tag, squash_from, tail_before_squash))) begin
                entries[cplt_tag].ready  <= 1'b1;
                entries[cplt_tag].result <= cplt_value;
                entries[cplt_tag].illegal<= cplt_illegal;
                entries[cplt_tag].halt   <= cplt_halt;
            end

            // 4) Dispatch
            if (disp_en && (rob_inc(T) != H)) begin
                entries[T].valid     <= 1'b1;
                entries[T].ready     <= 1'b0;
                entries[T].arch_dest <= disp_arch_dest;
                entries[T].has_dest  <= disp_has_dest;
                entries[T].result    <= '0;
                entries[T].NPC       <= disp_NPC;
                entries[T].illegal   <= 1'b0;
                entries[T].halt      <= 1'b0;
                disp_rob_tag         <= T;
                T = rob_inc(T);
            end

            tail <= T;
        end
    end

endmodule
