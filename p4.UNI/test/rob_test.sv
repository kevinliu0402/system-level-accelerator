/////////////////////////////////////////////////////////////////////////
//  Testbench for rob (Active List): OoO complete, in-order commit, squash
/////////////////////////////////////////////////////////////////////////

`include "verilog/sys_defs.svh"

module testbench;

    logic clock, reset;
    logic disp_en;
    logic [4:0] disp_arch_dest;
    logic disp_has_dest;
    logic [`XLEN-1:0] disp_NPC;
    logic disp_ready;
    logic [$clog2(`ROB_SZ)-1:0] disp_rob_tag;

    logic cplt_en;
    logic [$clog2(`ROB_SZ)-1:0] cplt_tag;
    logic [`XLEN-1:0] cplt_value;
    logic cplt_illegal;
    logic cplt_halt;

    logic squash_en;
    logic [$clog2(`ROB_SZ)-1:0] squash_from;

    logic rob_commit_valid;
    logic [4:0] rob_commit_arch_dest;
    logic rob_commit_has_dest;
    logic [`XLEN-1:0] rob_commit_value;
    logic rob_commit_wr_en;
    logic rob_commit_illegal;
    logic rob_commit_halt;
    logic [`XLEN-1:0] rob_commit_NPC;
    logic rob_empty;
    EXCEPTION_CODE rob_exception_status;

    rob dut (
        .clock(clock),
        .reset(reset),
        .disp_en(disp_en),
        .disp_arch_dest(disp_arch_dest),
        .disp_has_dest(disp_has_dest),
        .disp_NPC(disp_NPC),
        .disp_ready(disp_ready),
        .disp_rob_tag(disp_rob_tag),
        .cplt_en(cplt_en),
        .cplt_tag(cplt_tag),
        .cplt_value(cplt_value),
        .cplt_illegal(cplt_illegal),
        .cplt_halt(cplt_halt),
        .squash_en(squash_en),
        .squash_from(squash_from),
        .rob_commit_valid(rob_commit_valid),
        .rob_commit_arch_dest(rob_commit_arch_dest),
        .rob_commit_has_dest(rob_commit_has_dest),
        .rob_commit_value(rob_commit_value),
        .rob_commit_wr_en(rob_commit_wr_en),
        .rob_commit_illegal(rob_commit_illegal),
        .rob_commit_halt(rob_commit_halt),
        .rob_commit_NPC(rob_commit_NPC),
        .rob_empty(rob_empty),
        .rob_exception_status(rob_exception_status)
    );

    always begin
        #(`CLOCK_PERIOD / 2.0);
        clock = ~clock;
    end

    task automatic tick;
        @(negedge clock);
    endtask

    task automatic dispatch(input logic [4:0] rd, input has, input [`XLEN-1:0] npc);
        disp_en = 1;
        disp_arch_dest = rd;
        disp_has_dest = has;
        disp_NPC = npc;
        tick;
        disp_en = 0;
    endtask

    task automatic complete(
        input logic [$clog2(`ROB_SZ)-1:0] tag,
        input logic [`XLEN-1:0] val,
        input ill,
        input hl
    );
        cplt_en = 1;
        cplt_tag = tag;
        cplt_value = val;
        cplt_illegal = ill;
        cplt_halt = hl;
        tick;
        cplt_en = 0;
    endtask

    task automatic squash(input logic [$clog2(`ROB_SZ)-1:0] from);
        squash_en = 1;
        squash_from = from;
        tick;
        squash_en = 0;
    endtask

    initial begin
        $display("\n--- rob_test: starting ---\n");

        clock = 0;
        reset = 1;
        disp_en = 0;
        cplt_en = 0;
        squash_en = 0;
        cplt_illegal = 0;
        cplt_halt = 0;

        tick;
        reset = 0;
        tick;

        // Reset empties ROB
        if (!rob_empty) begin
            $display("@@@ Incorrect: expected rob_empty after reset");
            $finish;
        end

        // --- In-order commit after OoO complete ---
        dispatch(5'd1, 1, 32'h1000);  // tag 0
        dispatch(5'd2, 1, 32'h1004);  // tag 1
        dispatch(5'd3, 1, 32'h1008);  // tag 2
        if (disp_rob_tag != 4'd2) begin
            $display("@@@ Incorrect: last dispatch tag %d expected 2", disp_rob_tag);
            $finish;
        end

        // Complete out of order; retire order must remain 0,1,2 (arch 1,2,3)
        complete(1, 32'hdead_0001, 0, 0);
        complete(0, 32'hdead_0000, 0, 0);
        complete(2, 32'hdead_0002, 0, 0);
        // On complete(2) posedge, tag0 retires first (one commit per cycle)
        tick;
        if (!rob_commit_valid || rob_commit_arch_dest != 2 || rob_commit_value != 32'hdead_0001
                || !rob_commit_wr_en) begin
            $display("@@@ Incorrect commit after OoO (expect arch x2 / tag1 value)");
            $finish;
        end
        tick;
        if (!rob_commit_valid || rob_commit_arch_dest != 3 || rob_commit_value != 32'hdead_0002
                || !rob_commit_wr_en) begin
            $display("@@@ Incorrect final OoO commit (arch x3)");
            $finish;
        end
        tick;
        if (!rob_empty) begin
            $display("@@@ Incorrect: ROB should be empty");
            $finish;
        end

        // --- Branch squash: 5 uops, squash from tag 3 ---
        dispatch(5'd1, 1, 32'h2000);  // 0
        dispatch(5'd2, 1, 32'h2004);  // 1
        dispatch(5'd3, 1, 32'h2008);  // 2
        dispatch(5'd4, 1, 32'h200c);  // 3  wrong path from here
        dispatch(5'd5, 1, 32'h2010);  // 4

        squash(3);
        tick;
        complete(0, 32'habc0, 0, 0);
        tick;
        complete(1, 32'habc1, 0, 0);
        tick;
        complete(2, 32'habc2, 0, 0);
        tick;
        if (!rob_empty) begin
            $display("@@@ Incorrect: ROB empty after committing 0..2 post-squash");
            $finish;
        end

        // --- Complete suppressed when tag was squashed (late WB) ---
        dispatch(5'd1, 1, 32'h3000);
        dispatch(5'd2, 1, 32'h3004);
        squash(1);  // drop tag 1 only
        tick;
        // Late complete to squashed slot 1 should not create a valid entry
        cplt_en = 1;
        cplt_tag = 1;
        cplt_value = 32'hbad;
        cplt_illegal = 0;
        cplt_halt = 0;
        tick;
        cplt_en = 0;
        complete(0, 32'hgood, 0, 0);
        tick;
        if (!rob_commit_valid || rob_commit_value != 32'hgood) begin
            $display("@@@ Incorrect commit after squashed late WB");
            $finish;
        end
        tick;
        if (!rob_empty) begin
            $display("@@@ Incorrect: expected empty");
            $finish;
        end

        // --- Illegal at commit ---
        dispatch(5'd7, 1, 32'h4000);
        complete(0, 32'h0, 1, 0);  // illegal
        // complete() ends at negedge with head ready; commit not yet applied
        if (!rob_commit_valid || !rob_commit_illegal || rob_commit_wr_en) begin
            $display("@@@ Incorrect illegal commit");
            $finish;
        end
        if (rob_exception_status != ILLEGAL_INST) begin
            $display("@@@ Incorrect exception status on illegal");
            $finish;
        end
        tick;  // retire illegal uop
        if (!rob_empty) begin
            $display("@@@ Incorrect: ROB empty after illegal retire");
            $finish;
        end

        // --- Halt ---
        dispatch(`ZERO_REG, 0, 32'h5000);
        complete(0, 32'h0, 0, 1);
        if (!rob_commit_valid || !rob_commit_halt || rob_commit_wr_en) begin
            $display("@@@ Incorrect halt commit");
            $finish;
        end
        if (rob_exception_status != HALTED_ON_WFI) begin
            $display("@@@ Incorrect exception status on halt");
            $finish;
        end
        tick;

        $display("@@@ Passed\n");
        $finish;
    end

endmodule
