package com.demo;

import com.demo.BankAccount;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.function.Executable;

public class BankAccount_withdraw_Dbl_Test_Boundary_7 {


    @Test
    public void testWithdrawWithZeroAmount() {
        final BankAccount account = new BankAccount("owner", 100.0);

        Assertions.assertThrows(IllegalArgumentException.class, new Executable() {
            @Override
            public void execute() throws Throwable {
                account.withdraw(0.0);
            }
        });
    }

}
